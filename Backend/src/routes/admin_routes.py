from fastapi import APIRouter, Depends, HTTPException, Query,Header, status
from uuid import UUID
from typing import Optional , List
from datetime import datetime
from sqlalchemy.orm import Session
from src.schemas.user_response_schema import UserResponse, UserUpdate
from src.schemas.ride_dashboard_item import RideDashboardItem
from src.services.user_data import get_user_by_id, get_all_users
from src.services.admin_rides_service import (
    get_all_orders,
    get_future_orders,
    get_past_orders,
    get_orders_by_user,
    get_order_by_ride_id
)
from ..utils.database import get_db
from src.models.user_model import User , UserRole
from src.models.vehicle_model import Vehicle
from ..schemas.check_vehicle_schema import VehicleInspectionSchema
from ..schemas.vehicle_schema import VehicleOut , InUseVehicleOut , VehicleStatusUpdate
from ..utils.auth import token_check
from ..services.vehicle_service import get_vehicles_with_optional_status,update_vehicle_status,get_vehicle_by_id, vehicle_inspection_logic, get_available_vehicles_for_ride_by_id
from ..services.user_notification import send_admin_odometer_notification
from datetime import date, datetime, timedelta
from src.models.vehicle_inspection_model import VehicleInspection
from ..services.monthly_trip_counts import archive_last_month_stats
from sqlalchemy import func
from fastapi.responses import JSONResponse
from src.models.ride_model import Ride
from sqlalchemy import cast, Date

from ..schemas.audit_schema import AuditLogsSchema
from src.services.audit_service import get_all_audit_logs
from ..utils.socket_manager import sio
router = APIRouter()

@router.get("/orders", response_model=list[RideDashboardItem])
def fetch_all_orders(
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    return get_all_orders(db, status=status, from_date=from_date, to_date=to_date)

@router.get("/orders/future", response_model=list[RideDashboardItem])
def fetch_future_orders(
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    return get_future_orders(db, status=status, from_date=from_date, to_date=to_date)

@router.get("/orders/past", response_model=list[RideDashboardItem])
def fetch_past_orders(
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    return get_past_orders(db, status=status, from_date=from_date, to_date=to_date)

@router.get("/orders/user/{user_id}", response_model=list[RideDashboardItem])
def fetch_orders_by_user(user_id: UUID, db: Session = Depends(get_db)):
    return get_orders_by_user(db, user_id=user_id)

@router.get("/orders/ride/{ride_id}", response_model=RideDashboardItem)
def fetch_order_by_ride(ride_id: UUID, db: Session = Depends(get_db)):
    result = get_order_by_ride_id(db, ride_id=ride_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    return result

@router.get("/user-data", response_model=List[UserResponse])
def fetch_all_users(db: Session = Depends(get_db)):
    users = get_all_users(db)
    if not users:
        raise HTTPException(status_code=404, detail="Users not found")
    return users

@router.get("/user-data/{user_id}", response_model=UserResponse)
def fetch_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    result = get_user_by_id(db, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.patch("/user-data-edit/{user_id}", response_model=UserResponse)
def edit_user_by_id_route(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.employee_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)
    print("🟡 Incoming update:", update_data)

    # Check attributes before applying them
    for key, value in update_data.items():
        if not hasattr(user, key):
            print(f"⚠️ WARNING: User has no attribute '{key}' — skipping.")
        else:
            print(f"✅ Updating '{key}' to '{value}'")
            setattr(user, key, value)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print("❌ Commit failed:", e)
        raise HTTPException(status_code=500, detail="Failed to update user")

    db.refresh(user)
    return user

@router.get("/roles")
def get_roles():
    return [role.value for role in UserRole]


@router.post("/vehicle-inspection")
def vehicle_inspection(data: VehicleInspectionSchema, db: Session = Depends(get_db),payload: dict = Depends(token_check)):
    try:
        return vehicle_inspection_logic(data, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.patch("/{vehicle_id}/status")
def patch_vehicle_status(
    vehicle_id: UUID,
    status_update: VehicleStatusUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(token_check)
):
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        return {"error": "User ID not found in token"}, 401
     
    res=update_vehicle_status(vehicle_id, status_update.new_status, status_update.freeze_reason, db, user_id)
    new_status=res.new_status
    sio.emit('vehicle_status_updated', {
            "vehicle_id": str(vehicle_id),
            "status": new_status,
    })
    return res

@router.get("/vehicle/{vehicle_id}")
def get_vehicle_by_id_route(vehicle_id: str, db: Session = Depends(get_db)):
    return get_vehicle_by_id(vehicle_id, db)

@router.get("/{ride_id}/available-vehicles", response_model=List[VehicleOut])
def available_vehicles_for_ride(
    ride_id: UUID,
    db: Session = Depends(get_db)
):
    try:
        return get_available_vehicles_for_ride_by_id(db, ride_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/all-vehicles", response_model=List[VehicleOut])
def get_all_vehicles_route(status: Optional[str] = Query(None), db: Session = Depends(get_db)
    ,payload: dict = Depends(token_check)):
    vehicles = get_vehicles_with_optional_status(db, status)
    return vehicles


@router.post("/notifications/admin", include_in_schema=True,   dependencies=[] )
def send_admin_notification_simple_route(db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).first()  # Get any vehicle (you can adjust logic later if needed)
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle found.")

    notifications = send_admin_odometer_notification(vehicle.id, vehicle.odometer_reading)

    if not notifications:
        raise HTTPException(status_code=204, detail="No admins found or odometer below threshold.")

    return {
        "detail": "Notifications sent",
        "count": len(notifications),
        "vehicle_id": str(vehicle.id),
        "plate_number": vehicle.plate_number,
        "odometer_reading": vehicle.odometer_reading

    }


@router.get("/inspections/today", response_model=List[VehicleInspectionSchema])
def get_today_inspections(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)

    inspections = db.query(VehicleInspection).filter(
        VehicleInspection.inspection_date >= today_start,
        VehicleInspection.inspection_date < tomorrow_start
    ).all()

    return inspections

# This function will be called later by another function with a GET route.
@router.post("/stats/archive-last-month")
def archive_last_month_endpoint(db: Session = Depends(get_db)):
    archive_last_month_stats(db)
    return {"detail": "Archiving completed successfully"}


@router.get("/analytics/vehicle-status-summary")
def vehicle_status_summary(db: Session = Depends(get_db)):
    try:
        result = (
            db.query(Vehicle.status, func.count(Vehicle.id).label("count"))
            .group_by(Vehicle.status)
            .all()
        )
        # Format response as a list of dicts
        summary = [{"status": row.status.value, "count": row.count} for row in result]
        return JSONResponse(content=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")

@router.get("/analytics/ride-status-summary")
def ride_status_summary(db: Session = Depends(get_db)):
    try:
        result = (
            db.query(Ride.status, func.count(Ride.id).label("count"))
            .group_by(Ride.status)
            .all()
        )
        summary = [{"status": row.status.value, "count": row.count} for row in result]
        return JSONResponse(content=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ride summary: {str(e)}")


# @router.get("/analytics/weekly-ride-trends")
# def weekly_ride_trends(db: Session = Depends(get_db)):
#     try:
#         today = datetime.utcnow().date()
#         week_ago = today - timedelta(days=6)  # last 7 days including today

#         # Group by date, count rides
#         results = (
#             db.query(
#                 cast(Ride.start_datetime, Date).label("ride_date"),
#                 func.count(Ride.id).label("count")
#             )
#             .filter(Ride.start_datetime >= week_ago)
#             .group_by("ride_date")
#             .order_by("ride_date")
#             .all()
#         )

#         # Convert to list of dicts
#         response = [{"date": str(r.ride_date), "count": r.count} for r in results]

#         return JSONResponse(content=response)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch weekly ride trends: {str(e)}")




@router.post("/update-monthly-trip-counts")
def monthly_trip_count_update(db: Session = Depends(get_db)):
    try:
        update_monthly_trip_counts(db)
        return {"message": "Monthly trip counts updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all-audit-logs", response_model=List[AuditLogsSchema])
def get_all_audit_logs_route(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    payload: dict = Depends(token_check)
):
    try:
        return get_all_audit_logs(db, from_date=from_date, to_date=to_date)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")