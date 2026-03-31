import { useState, useEffect, useCallback } from 'react';
import { Job, BacklogSummary, CustomerSummary, BacklogUtilization } from './backlogTypes';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Check if auth is enabled
const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true';

export interface JobsResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseBacklogDataResult {
  // Data
  jobs: Job[];
  summary: BacklogSummary | null;
  customers: CustomerSummary[];
  utilization: BacklogUtilization[];
  
  // Loading states
  isLoading: boolean;
  isLoadingJobs: boolean;
  
  // Error state
  error: string | null;
  
  // Refetch functions
  refetchJobs: (params?: FetchJobsParams) => Promise<Job[]>;
  refetchSummary: () => Promise<BacklogSummary | null>;
  refetchCustomers: () => Promise<CustomerSummary[]>;
  
  // Total count
  totalJobs: number;
}

export interface FetchJobsParams {
  limit?: number;
  offset?: number;
  customerName?: string;
  jobType?: 'Fixed Price' | 'Time and Materials' | 'Modernization';
  laborType?: 'Crew' | 'Mechanic' | 'Contractor';
  readyToWork?: boolean;
  finalBillMonth?: string;
  minSellingAmount?: number;
  maxSellingAmount?: number;
}

/**
 * Custom hook for fetching backlog data from REST API.
 * Loads initial data on mount and provides refetch functions for updates.
 * @param initialLimit - Maximum number of jobs to fetch initially
 * @param accessToken - Optional access token for authenticated requests
 */
export function useBacklogData(initialLimit: number = 100, accessToken?: string | null): UseBacklogDataResult {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<BacklogSummary | null>(null);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [utilization, setUtilization] = useState<BacklogUtilization[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Build headers with optional auth
  const getHeaders = useCallback((): HeadersInit => {
    const headers: HeadersInit = {};
    if (accessToken && isAuthEnabled) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    return headers;
  }, [accessToken]);

  // Fetch jobs with optional filtering/pagination
  const fetchJobs = useCallback(async (params: FetchJobsParams = {}): Promise<Job[]> => {
    const {
      limit = initialLimit,
      offset = 0,
      customerName,
      jobType,
      laborType,
      readyToWork,
      finalBillMonth,
      minSellingAmount,
      maxSellingAmount,
    } = params;

    const queryParams = new URLSearchParams();
    queryParams.set('limit', limit.toString());
    queryParams.set('offset', offset.toString());
    
    if (customerName) queryParams.set('customer_name', customerName);
    if (jobType) queryParams.set('job_type', jobType);
    if (laborType) queryParams.set('labor_type', laborType);
    if (readyToWork !== undefined) queryParams.set('ready_to_work', readyToWork.toString());
    if (finalBillMonth) queryParams.set('final_bill_month', finalBillMonth);
    if (minSellingAmount !== undefined) queryParams.set('min_selling_amount', minSellingAmount.toString());
    if (maxSellingAmount !== undefined) queryParams.set('max_selling_amount', maxSellingAmount.toString());

    setIsLoadingJobs(true);
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/backlog?${queryParams}`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`);
      }
      const data: JobsResponse = await response.json();
      setJobs(data.jobs);
      setTotalJobs(data.total);
      setError(null);
      return data.jobs;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch jobs';
      setError(message);
      console.error('[useBacklogData] Error fetching jobs:', err);
      return [];
    } finally {
      setIsLoadingJobs(false);
    }
  }, [initialLimit, getHeaders]);

  // Fetch backlog summary
  const fetchSummary = useCallback(async (): Promise<BacklogSummary | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/backlog-summary`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch summary: ${response.statusText}`);
      }
      const data: BacklogSummary = await response.json();
      setSummary(data);
      return data;
    } catch (err) {
      console.error('[useBacklogData] Error fetching summary:', err);
      return null;
    }
  }, [getHeaders]);

  // Fetch customer summaries
  const fetchCustomers = useCallback(async (): Promise<CustomerSummary[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/backlog-customers`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch customers: ${response.statusText}`);
      }
      const data: CustomerSummary[] = await response.json();
      setCustomers(data);
      return data;
    } catch (err) {
      console.error('[useBacklogData] Error fetching customers:', err);
      return [];
    }
  }, [getHeaders]);

  // Fetch utilization data
  const fetchUtilization = useCallback(async (): Promise<BacklogUtilization[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/backlog-utilization`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch utilization: ${response.statusText}`);
      }
      const data: BacklogUtilization[] = await response.json();
      setUtilization(data);
      return data;
    } catch (err) {
      console.error('[useBacklogData] Error fetching utilization:', err);
      return [];
    }
  }, [getHeaders]);

  // Load initial data on mount
  useEffect(() => {
    fetchJobs();
    fetchSummary();
    fetchCustomers();
    fetchUtilization();
  }, [fetchJobs, fetchSummary, fetchCustomers, fetchUtilization]);

  return {
    // Data
    jobs,
    summary,
    customers,
    utilization,
    
    // Loading states
    isLoading: isLoadingJobs,
    isLoadingJobs,
    
    // Error state
    error,
    
    // Refetch functions
    refetchJobs: fetchJobs,
    refetchSummary: fetchSummary,
    refetchCustomers: fetchCustomers,
    
    // Total count
    totalJobs,
  };
}
