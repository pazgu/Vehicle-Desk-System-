from ..services.vehicle_service import get_vehicles_with_optional_status,update_vehicle_status,get_vehicle_by_id, vehicle_inspection_logic, get_available_vehicles_for_ride_by_id
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from ..schemas.vehicle_schema import VehicleStatusUpdate
from ..utils.socket_manager import sio
from sqlalchemy.orm import Session
from ..schemas.vehicle_schema import VehicleOut
from ..schemas.check_vehicle_schema import VehicleInspectionSchema
from ..utils.auth import token_check
from ..utils.database import get_db
from typing import List, Optional, Union

router = APIRouter()

@router.post("/vehicle-inspection")
def vehicle_inspection(data: VehicleInspectionSchema, db: Session = Depends(get_db),payload: dict = Depends(token_check)):
    try:
        return vehicle_inspection_logic(data, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/all-vehicles", response_model=List[VehicleOut])
def get_all_vehicles_route(status: Optional[str] = Query(None), db: Session = Depends(get_db)
    ,payload: dict = Depends(token_check)):
    vehicles = get_vehicles_with_optional_status(db, status)
    return vehicles



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
    new_status=res["new_status"]
    sio.emit('vehicle_status_updated', {
            "vehicle_id": str(vehicle_id),
            "status": new_status,
            "freeze_reason": res.get("freeze_reason", "")
    })
    return res



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


@router.get("/vehicle/{vehicle_id}")
def get_vehicle_by_id_route(vehicle_id: str, db: Session = Depends(get_db)):
    return get_vehicle_by_id(vehicle_id, db)
