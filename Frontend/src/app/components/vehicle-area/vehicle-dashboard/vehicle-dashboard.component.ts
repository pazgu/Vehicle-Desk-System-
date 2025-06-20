import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VehicleService } from '../../../services/vehicle.service';
import { CardModule } from 'primeng/card';
import { VehicleOutItem } from '../../../models/vehicle-dashboard-item/vehicle-out-item.module';
import { VehicleInItem } from '../../../models/vehicle-dashboard-item/vehicle-in-use-item.module';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-vehicle-dashboard',
  imports: [CommonModule, FormsModule, CardModule],
  templateUrl: './vehicle-dashboard.component.html',
  styleUrl: './vehicle-dashboard.component.css'
})
export class VehicleDashboardComponent {

  vehicles: VehicleInItem[] = [];
  selectedType: string = '';
  statusFilter: string = '';
  typeFilter: string = '';
  showFilters: boolean = false;
  sortBy: string = 'date_and_time';
  
  // Enhanced usage tracking from analytics component
  topUsedVehiclesMap: Record<string, number> = {};
  vehicleUsageData: { plate_number: string; vehicle_model: string; ride_count: number }[] = [];

  constructor(
    private vehicleService: VehicleService, 
    private router: Router,
    private http: HttpClient
  ){}

  ngOnInit(): void {
    this.loadVehicles();
    this.loadVehicleUsageData();
  }

  goToVehicleDetails(vehicleId: string): void {
    this.router.navigate(['/vehicle-details', vehicleId]);
  }

  loadVehicles(): void{
    this.vehicleService.getAllVehicles().subscribe(
      (data) => {
        this.vehicles = Array.isArray(data) ? data : [];
        console.log('Vehicles loaded:', this.vehicles);
      },
      (error) => {
        console.error('Error loading vehicles:', error);
      }
    );
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

  // Get usage count for a specific vehicle
  getVehicleUsageCount(plateNumber: string): number {
    return this.topUsedVehiclesMap[plateNumber] || 0;
  }

  // Get usage level classification
  getUsageLevel(plateNumber: string): 'high' | 'medium' | 'good' | 'hide'{
    const count = this.getVehicleUsageCount(plateNumber);
    if (count > 10) return 'high';
    if (count >= 5) return 'medium';
    if (count == 0 ) return 'hide';
    return 'good';
  }

 
  // Get usage bar color
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
  // Get usage bar width percentage (0-100%)
  getUsageBarWidth(plateNumber: string): number {
    const count = this.getVehicleUsageCount(plateNumber);
    // Scale to max 15 rides for 100% width
    const maxRides = 15;
    return Math.min((count / maxRides) * 100, 100);
  }

  getCardClass(status: string | null | undefined): string {
    if (!status) return '';
    switch (status) {
      case 'available':
        return 'card-available';
      case 'in_use':
        return 'card-inuse';
      case 'frozen':
        return 'card-frozen';
      default:
        return '';
    }
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
  
  get filteredVehicles() {
    if (!this.vehicles) {
        return [];
    }
    let filtered = [...this.vehicles];

    if (this.statusFilter) {
      switch (this.statusFilter) {
        case 'זמין':
          filtered = filtered.filter(vehicle => vehicle.status === 'available');
          break;
        case 'בשימוש':
          filtered = filtered.filter(vehicle => vehicle.status === 'in_use');
          break;
        case 'מוקפא':
          filtered = filtered.filter(vehicle => vehicle.status === 'frozen');
          break;
        default:
          break;
      }
    }

    if (this.typeFilter) {
      switch (this.typeFilter) {
        case 'קטן':
          filtered = filtered.filter(vehicle => vehicle.type === 'small');
          break;
        case 'גדול':
          filtered = filtered.filter(vehicle => vehicle.type === 'large');
          break;
        case 'ואן':
          filtered = filtered.filter(vehicle => vehicle.type === 'van');
          break;
        default:
          break;
      }
    }

    if (this.sortBy){
      return [...filtered].sort((a, b) => a.status.localeCompare(b.status));
    }
    else{
      return filtered;
    }
  }
}