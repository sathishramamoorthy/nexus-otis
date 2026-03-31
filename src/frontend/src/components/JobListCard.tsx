import { useState } from 'react';
import { Job, getReadinessLabel, getReadinessColor } from '@/lib/backlogTypes';

interface JobListCardProps {
  jobs: Job[];
  selectedJobId?: string | null;
  onSelectJob?: (job: Job) => void;
  highlightReady: boolean;
  pageSize?: number;
  minItems?: number;
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

// Readiness badge component
function ReadinessBadge({ job }: { job: Job }) {
  const label = getReadinessLabel(job);
  const color = getReadinessColor(job);
  
  return (
    <span 
      className="px-2 py-1 rounded-full text-xs font-medium"
      style={{ 
        backgroundColor: `${color}20`,
        color: color,
      }}
    >
      {label}
    </span>
  );
}

export function JobListCard({ 
  jobs, 
  selectedJobId, 
  onSelectJob, 
  highlightReady,
  pageSize = 5,
  minItems = 5
}: JobListCardProps) {
  // Ensure we show at least minItems if available
  const effectivePageSize = Math.max(pageSize, Math.min(minItems, jobs?.length || 0));
  const [currentPage, setCurrentPage] = useState(1);
  
  if (!jobs || jobs.length === 0) {
    return (
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 w-full">
        <h2 className="text-xl font-bold text-white mb-4">Workable Backlog</h2>
        <p className="text-gray-300 text-center py-8">
          No jobs to display. Ask the assistant to show backlog data!
        </p>
      </div>
    );
  }

  // Sort jobs by selling amount (descending)
  const sortedJobs = [...jobs].sort((a, b) => b.sellingAmount - a.sellingAmount);

  const totalJobs = sortedJobs.length;
  const totalPages = Math.ceil(totalJobs / effectivePageSize);
  const startIndex = (currentPage - 1) * effectivePageSize;
  const endIndex = Math.min(startIndex + effectivePageSize, totalJobs);
  const displayedJobs = sortedJobs.slice(startIndex, endIndex);

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  return (
    <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 w-full overflow-hidden flex flex-col flex-shrink-0">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h2 className="text-xl font-bold text-white">Workable Backlog</h2>
        <span className="text-sm text-gray-300 whitespace-nowrap">
          Showing {startIndex + 1}-{endIndex} of {totalJobs} jobs
        </span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/20">
              <th className="pb-2 pr-4 text-sm font-semibold text-gray-300">Job ID</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300">Customer</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300">Type</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300 text-right">Amount</th>
              <th className="pb-2 pl-4 text-sm font-semibold text-gray-300">Status</th>
            </tr>
          </thead>
          <tbody>
            {displayedJobs.map((job, index) => {
              const isSelected = selectedJobId === job.jobId;
              const rowBgColor = highlightReady && job.readyToWork 
                ? 'bg-green-500/10' 
                : highlightReady && job.customerDelay
                ? 'bg-orange-500/10'
                : isSelected 
                ? 'bg-white/10' 
                : '';
              
              return (
                <tr 
                  key={job.jobId || `job-${index}`}
                  onClick={() => onSelectJob?.(job)}
                  className={`border-b border-white/10 cursor-pointer hover:bg-white/10 transition-colors ${rowBgColor}`}
                >
                  <td className="py-2 pr-4 text-white font-medium">{job.jobId || '—'}</td>
                  <td className="py-2 px-4 text-gray-300 max-w-[200px] truncate" title={job.customerName}>
                    {job.customerName || '—'}
                  </td>
                  <td className="py-2 px-4 text-gray-300">{job.jobType || '—'}</td>
                  <td className="py-2 px-4 text-right">
                    <span className="font-semibold text-white">
                      {formatCurrency(job.sellingAmount)}
                    </span>
                  </td>
                  <td className="py-2 pl-4">
                    <ReadinessBadge job={job} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1 text-sm rounded bg-white/10 text-gray-300 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            ← Previous
          </button>
          
          <div className="flex items-center gap-1 overflow-hidden">
            {(() => {
              // Show limited page numbers with ellipsis
              const maxVisible = 7;
              const pages: (number | string)[] = [];
              
              if (totalPages <= maxVisible) {
                // Show all pages
                for (let i = 1; i <= totalPages; i++) pages.push(i);
              } else {
                // Always show first page
                pages.push(1);
                
                if (currentPage > 3) {
                  pages.push('...');
                }
                
                // Show pages around current
                const start = Math.max(2, currentPage - 1);
                const end = Math.min(totalPages - 1, currentPage + 1);
                
                for (let i = start; i <= end; i++) {
                  if (!pages.includes(i)) pages.push(i);
                }
                
                if (currentPage < totalPages - 2) {
                  pages.push('...');
                }
                
                // Always show last page
                if (!pages.includes(totalPages)) pages.push(totalPages);
              }
              
              return pages.map((page, idx) => (
                typeof page === 'string' ? (
                  <span key={`ellipsis-${idx}`} className="px-1 text-gray-500">...</span>
                ) : (
                  <button
                    key={page}
                    onClick={() => goToPage(page)}
                    className={`w-8 h-8 text-sm rounded transition-colors flex-shrink-0 ${
                      page === currentPage
                        ? 'bg-white/20 text-white font-semibold'
                        : 'text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    {page}
                  </button>
                )
              ));
            })()}
          </div>
          
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 text-sm rounded bg-white/10 text-gray-300 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
