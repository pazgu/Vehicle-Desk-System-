import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { VehicleService } from '../../../services/vehicle.service';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
@Component({
  selector: 'app-vehicle-card-item',
  templateUrl: './vehicle-card-item.component.html',
  styleUrls: ['./vehicle-card-item.component.css'],
  imports: [CommonModule, CardModule, FormsModule],
})
export class VehicleCardItemComponent implements OnInit {
  vehicle: any;
  isFreezeReasonFieldVisible: boolean = false; // Controls visibility of the input field
  freezeReason: string = ''; // Holds the freeze reason entered by the user
  topUsedVehiclesMap: Record<string, number> = {};
  vehicleUsageData: { plate_number: string; vehicle_model: string; ride_count: number }[] = [];

  constructor(private navigateRouter: Router, private route: ActivatedRoute, private vehicleService: VehicleService, private http: HttpClient) { }

  ngOnInit(): void {
     window.scrollTo({ top: 0, behavior: 'smooth' });

  this.loadVehicleUsageData(); // ✅ Add this line to fetch usage data

  const id = this.route.snapshot.paramMap.get('id');
  if (id) {
    this.vehicleService.getVehicleById(id).subscribe(data => {
      console.log('Vehicle from API:', data);
      this.vehicle = data;
    });
  }
  }

  getCardClass(status: string): string {
    switch (status) {
      case 'available': return 'card-available';
      case 'in_use': return 'card-inuse';
      case 'frozen': return 'card-frozen';
      default: return '';
    }
  }

  goBack(): void {
    window.history.back();
  }

  // New method to load vehicle usage data from analytics
  loadVehicleUsageData(): void {
    this.http.get<{ plate_number: string; vehicle_model: string; ride_count: number }[]>(
      `${environment.apiUrl}/analytics/top-used-vehicles`
    ).subscribe({
      next: data => {
        this.vehicleUsageData = data;
        // Create a map for quick lookup
        this.topUsedVehiclesMap = {};
        data.forEach(vehicle => {
          this.topUsedVehiclesMap[vehicle.plate_number] = vehicle.ride_count;
        });
        console.log('Vehicle usage data loaded:', this.topUsedVehiclesMap);
      },
      error: err => {
        console.error('❌ Error fetching vehicle usage data:', err);
      }
    });
  }
  translateStatus(status: string | null | undefined): string {
    if (!status) return '';
    switch (status.toLowerCase()) {
      case 'available':
        return 'זמין';
      case 'in_use':
        return 'בשימוש';
      case 'frozen':
        return 'מוקפא';
      default:
        return status;
    }
  }

  translateType(type: string | null | undefined): string {
    if (!type) return '';
    switch (type.toLowerCase()) {
      case 'small':
        return 'קטן';
      case 'large':
        return 'גדול';
      case 'van':
        return 'מסחרי';
      default:
        return type;
    }
  }

  translateFuelType(fuelType: string | null | undefined): string {
    if (!fuelType) return '';
    switch (fuelType.toLowerCase()) {
      case 'electric':
        return 'חשמלי';
      case 'hybrid':
        return 'היברידי';
      case 'gasoline':
        return 'בנזין';
      default:
        return fuelType;
    }
  }

  translateFreezeReason(freezeReason: string | null | undefined): string {
    if (!freezeReason) return '';
    switch (freezeReason.toLowerCase()) {
      case 'accident':
        return 'תאונה';
      case 'maintenance':
        return 'תחזוקה';
      case 'personal':
        return 'אישי';
      default:
        return freezeReason;
    }
  }

  // Modified updateVehicleStatus to accept the new status and optionally the freeze reason
  updateVehicleStatus(newStatus: string, reason?: string): void {
    if (!this.vehicle?.id) return;
  
    this.vehicleService.updateVehicleStatus(this.vehicle.id, newStatus, reason).subscribe({
      next: (response) => {
        console.log(`Vehicle status updated to '${newStatus}':`, response);
        this.vehicle.status = newStatus; // Update the local status
        this.vehicle.freeze_reason = newStatus === 'frozen' ? reason : null; // Clear freeze reason if unfreezing
  
        // Reset the dropdown and hide it if freezing
        if (newStatus === 'frozen') {
          this.freezeReason = '';
          this.isFreezeReasonFieldVisible = false;
        }
      },
      error: (err) => {
        console.error(`Failed to update vehicle status to '${newStatus}':`, err);
        alert(`Failed to update vehicle status: ${err.error?.detail || err.message}`);
      }
    });
    this.navigateRouter.navigate(['/vehicle-dashboard']); // או הנתיב המתאים שלך
  }

  
  // Show the freeze reason input field
  showFreezeReasonField(): void {
    this.isFreezeReasonFieldVisible = true;
  }

  // Freeze the vehicle with the entered reason
  freezeStatus(): void {
    if (!this.freezeReason.trim()) {
      alert('יש להזין סיבת הקפאה');
      return;
  }

    console.log('Freezing vehicle with reason:', this.freezeReason); // Log the freeze reason

    // Call the common updateVehicleStatus method with 'frozen' status and the reason
    this.updateVehicleStatus('frozen', this.freezeReason);

    // Reset the dropdown and hide it after successful freeze (or if error occurs, the UI will reflect actual state)
    this.freezeReason = '';
    this.isFreezeReasonFieldVisible = false;

  }

   getUsageBarColor(plateNumber: string): string {
    const level = this.getUsageLevel(plateNumber);
    switch (level) {
      case 'high': return '#FF5252';    // Red
      case 'medium': return '#FFC107';  // Yellow
      case 'good': return '#42A5F5';    // Blue
      case 'hide': return'rgba(255, 255, 255, 0)'// Gray (hidden)
      default: return '#E0E0E0';        // Gray
    }
  }
   getUsageLevel(plateNumber: string): 'high' | 'medium' | 'good' | 'hide'{
    const count = this.getVehicleUsageCount(plateNumber);
    if (count > 10) return 'high';
    if (count >= 5) return 'medium';
    if (count == 0 ) return 'hide';
    return 'good';
  }
  // Get usage bar width percentage (0-100%)
  getUsageBarWidth(plateNumber: string): number {
    const count = this.getVehicleUsageCount(plateNumber);
    // Scale to max 15 rides for 100% width
    const maxRides = 15;
    return Math.min((count / maxRides) * 100, 100);
  }
    getVehicleUsageCount(plateNumber: string): number {
    return this.topUsedVehiclesMap[plateNumber] || 0;
  }
}