import { useState } from 'react';
import { Job } from '@/lib/backlogTypes';

export interface JobStatusUpdate {
  jobId: string;
  field: 'downPaymentReceived' | 'permitReceived' | 'materialOrdered' | 'materialOnHand' | 'customerDelay';
  value: boolean;
}

interface JobDetailCardProps {
  job: Job;
  themeColor: string;
  onClose?: () => void;
  onStatusChange?: (update: JobStatusUpdate) => void;
}

// Format currency for display
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// Format date for display
function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// Briefcase icon for jobs
function BriefcaseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
      <path fillRule="evenodd" d="M7.5 5.25a3 3 0 013-3h3a3 3 0 013 3v.205c.933.085 1.857.197 2.774.334 1.454.218 2.476 1.483 2.476 2.917v3.033c0 1.211-.734 2.352-1.936 2.752A24.726 24.726 0 0112 15.75c-2.73 0-5.357-.442-7.814-1.259-1.202-.4-1.936-1.541-1.936-2.752V8.706c0-1.434 1.022-2.7 2.476-2.917A48.814 48.814 0 017.5 5.455V5.25zm7.5 0v.09a49.488 49.488 0 00-6 0v-.09a1.5 1.5 0 011.5-1.5h3a1.5 1.5 0 011.5 1.5zm-3 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clipRule="evenodd" />
      <path d="M3 18.4v-2.796a4.3 4.3 0 00.713.31A26.226 26.226 0 0012 17.25c2.892 0 5.68-.468 8.287-1.335.252-.084.49-.189.713-.311V18.4c0 1.452-1.047 2.728-2.523 2.923-2.12.282-4.282.427-6.477.427a49.19 49.19 0 01-6.477-.427C4.047 21.128 3 19.852 3 18.4z" />
    </svg>
  );
}

// Progress bar for margin
function MarginBar({ projected, selling }: { projected: number; selling: number }) {
  const safeSelling = selling || 1;
  const percentage = Math.min((projected / safeSelling) * 100, 100);
  
  const barColor = percentage > 30 
    ? '#22c55e' 
    : percentage > 15 
    ? '#f97316' 
    : '#ef4444';

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-300">Projected Margin</span>
        <span className="text-white font-medium">
          {formatCurrency(projected)} ({percentage.toFixed(1)}%)
        </span>
      </div>
      <div className="h-3 bg-white/20 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${percentage}%`,
            backgroundColor: barColor
          }}
        />
      </div>
    </div>
  );
}

// Status toggle component
function StatusToggle({ 
  label, 
  value, 
  positive, 
  onChange 
}: { 
  label: string; 
  value: boolean; 
  positive?: boolean;
  onChange: (value: boolean) => void;
}) {
  const isGood = positive ? value : !value;
  
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-gray-300 text-sm">{label}</span>
      <button
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 ${
          value 
            ? (isGood ? 'bg-green-500 focus:ring-green-500' : 'bg-orange-500 focus:ring-orange-500')
            : 'bg-gray-600 focus:ring-gray-500'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            value ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

export function JobDetailCard({ job, themeColor, onClose, onStatusChange }: JobDetailCardProps) {
  // Local state for checklist items
  const [downPaymentReceived, setDownPaymentReceived] = useState(job.downPaymentReceived);
  const [permitReceived, setPermitReceived] = useState(job.permitReceived);
  const [materialOrdered, setMaterialOrdered] = useState(job.materialOrdered);
  const [materialOnHand, setMaterialOnHand] = useState(job.materialOnHand);
  const [customerDelay, setCustomerDelay] = useState(job.customerDelay);
  
  // Compute readiness dynamically based on local state
  const computeReadinessLabel = (): string => {
    if (job.workCompleted) return 'Completed';
    if (customerDelay) return 'Customer Delay';
    if (!permitReceived) return 'Awaiting Permit';
    if (!materialOnHand) return 'Awaiting Material';
    if (!downPaymentReceived) return 'Awaiting Payment';
    // All conditions met = Ready
    return 'Ready';
  };

  const computeReadinessColor = (): string => {
    if (job.workCompleted) return '#6b7280'; // gray - completed
    if (customerDelay) return '#f97316'; // orange - delayed
    if (!permitReceived || !materialOnHand || !downPaymentReceived) return '#3b82f6'; // blue - pending
    return '#22c55e'; // green - ready
  };

  const readinessLabel = computeReadinessLabel();
  const readinessColor = computeReadinessColor();

  const handleStatusChange = (
    field: JobStatusUpdate['field'],
    value: boolean,
    setter: (value: boolean) => void
  ) => {
    setter(value);
    onStatusChange?.({
      jobId: job.jobId,
      field,
      value,
    });
  };

  return (
    <div 
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl w-full"
    >
      <div className="bg-white/20 backdrop-blur-md p-6 rounded-xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl text-white">
              <BriefcaseIcon />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white">{job.jobId}</h3>
              <p className="text-gray-200">{job.customerName}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span 
              className="px-3 py-1 rounded-full text-sm font-medium"
              style={{ 
                backgroundColor: `${readinessColor}20`,
                color: readinessColor,
              }}
            >
              {readinessLabel}
            </span>
            {onClose && (
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Project Info */}
        <div className="bg-white/10 rounded-lg p-4 mb-6">
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Project Description</h4>
          <p className="text-white">{job.projectDescription}</p>
          <p className="text-sm text-gray-400 mt-2">{job.jobSiteAddress}</p>
        </div>

        {/* Financial Summary */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white/10 rounded-lg p-4">
            <div className="text-sm text-gray-300 mb-1">Selling Amount</div>
            <div className="text-2xl font-bold text-white">{formatCurrency(job.sellingAmount)}</div>
          </div>
          <div className="bg-white/10 rounded-lg p-4">
            <div className="text-sm text-gray-300 mb-1">Estimated Cost</div>
            <div className="text-2xl font-bold text-white">{formatCurrency(job.estimatedCost)}</div>
          </div>
        </div>

        {/* Margin Bar */}
        <div className="bg-white/10 rounded-lg p-4 mb-6">
          <MarginBar projected={job.projectedMargin} selling={job.sellingAmount} />
        </div>

        {/* Timeline */}
        <div className="bg-white/10 rounded-lg p-4 mb-6">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Timeline</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-gray-400">Scheduled Start</div>
              <div className="text-white font-medium">{formatDate(job.scheduledStartDate)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Projected Completion</div>
              <div className="text-white font-medium">{formatDate(job.projectedCompletionDate)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Material ETA</div>
              <div className="text-white font-medium">{formatDate(job.materialEtaDate)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Bill Date</div>
              <div className="text-white font-medium">{formatDate(job.dateToBill)}</div>
            </div>
          </div>
        </div>

        {/* Status Checklist */}
        <div className="bg-white/10 rounded-lg p-4 mb-6">
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Status Checklist</h4>
          <div className="divide-y divide-white/10">
            <StatusToggle 
              label="Down Payment Received" 
              value={downPaymentReceived} 
              positive 
              onChange={(v) => handleStatusChange('downPaymentReceived', v, setDownPaymentReceived)}
            />
            <StatusToggle 
              label="Permit Received" 
              value={permitReceived} 
              positive 
              onChange={(v) => handleStatusChange('permitReceived', v, setPermitReceived)}
            />
            <StatusToggle 
              label="Material Ordered" 
              value={materialOrdered} 
              positive 
              onChange={(v) => handleStatusChange('materialOrdered', v, setMaterialOrdered)}
            />
            <StatusToggle 
              label="Material On Hand" 
              value={materialOnHand} 
              positive 
              onChange={(v) => handleStatusChange('materialOnHand', v, setMaterialOnHand)}
            />
            <StatusToggle 
              label="Customer Delay" 
              value={customerDelay} 
              positive={false} 
              onChange={(v) => handleStatusChange('customerDelay', v, setCustomerDelay)}
            />
          </div>
        </div>

        {/* Labor Info */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-300">Labor Type:</span>
            <span className="text-white font-medium">{job.laborType}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-300">Job Type:</span>
            <span className="text-white font-medium">{job.jobType}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-300">Bill Month:</span>
            <span className="text-white font-medium">{job.finalBillMonth}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
