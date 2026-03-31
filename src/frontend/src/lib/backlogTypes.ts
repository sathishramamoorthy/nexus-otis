// Backlog Agent State Types

export interface Job {
  jobId: string;
  jobType: 'Fixed Price' | 'Time and Materials' | 'Modernization';
  customerName: string;
  jobSiteAddress: string;
  projectDescription: string;
  downPaymentReceived: boolean;
  downPaymentPercent: number;
  customerDelay: boolean;
  permitReceived: boolean;
  materialOrdered: boolean;
  materialOnHand: boolean;
  materialLeadTimeWeeks: number;
  materialEtaDate: string;
  scheduledStartDate: string;
  projectedCompletionDate: string;
  dateToBill: string;
  finalBillMonth: string;
  sellingAmount: number;
  estimatedCost: number;
  actualCost: number;
  projectedMargin: number;
  actualMargin: number;
  soldHours: number;
  taskHours: number;
  laborType: 'Crew' | 'Mechanic' | 'Contractor';
  workCompleted: boolean;
  removeFromJobSheet: boolean;
  readyToWork: boolean;
  workableBacklogAmount: number;
}

// Filter criteria for backlog dashboard filtering
export interface BacklogFilter {
  filterType: 'all' | 'customer' | 'jobType' | 'laborType' | 'readiness' | 'billing' | 'combined';
  customerName?: string | null;
  jobType?: 'Fixed Price' | 'Time and Materials' | 'Modernization' | null;
  laborType?: 'Crew' | 'Mechanic' | 'Contractor' | null;
  readyToWork?: boolean | null;
  finalBillMonth?: string | null;
  minSellingAmount?: number | null;
  maxSellingAmount?: number | null;
  limit?: number | null;
}

// Default filter showing all jobs
export const DEFAULT_BACKLOG_FILTER: BacklogFilter = { filterType: 'all' };

// Backlog summary for display (matches backend response)
export interface BacklogSummary {
  totalJobs: number;
  totalSellingAmount: number;
  totalWorkableBacklog: number;
  totalProjectedMargin: number;
  averageJobValue: number;
  readyToWork: number;
  notReadyToWork: number;
  uniqueCustomers: number;
  jobTypeBreakdown: Record<string, number>;
  laborTypeBreakdown: Record<string, number>;
  revenueByMonth: Record<string, number>;
}

// Customer summary data
export interface CustomerSummary {
  customerName: string;
  jobCount: number;
  totalBacklogAmount: number;
  readyJobs: number;
}

// Utilization data
export interface BacklogUtilization {
  month: string;
  laborType: string;
  plannedHours: number;
  availableHours: number;
  utilizationPercent: number;
}

export interface BacklogAgentState {
  jobs: Job[];
  selectedJob: Job | null;
  utilizationData: BacklogUtilization[];
  viewMode: 'list' | 'detail';
  activeFilter: BacklogFilter;
}

// Initial empty state - data is fetched from REST API on page load
export const initialBacklogState: BacklogAgentState = {
  jobs: [],
  selectedJob: null,
  utilizationData: [],
  viewMode: 'list',
  activeFilter: DEFAULT_BACKLOG_FILTER,
};

// Helper to get readiness status label
export function getReadinessLabel(job: Job): string {
  if (job.workCompleted) return 'Completed';
  if (job.readyToWork) return 'Ready';
  if (job.customerDelay) return 'Customer Delay';
  if (!job.permitReceived) return 'Awaiting Permit';
  if (!job.materialOnHand) return 'Awaiting Material';
  if (!job.downPaymentReceived) return 'Awaiting Payment';
  return 'Not Ready';
}

// Helper to get readiness color
export function getReadinessColor(job: Job): string {
  if (job.workCompleted) return '#6b7280'; // gray - completed
  if (job.readyToWork) return '#22c55e'; // green - ready
  if (job.customerDelay) return '#f97316'; // orange - delayed
  return '#3b82f6'; // blue - pending
}
