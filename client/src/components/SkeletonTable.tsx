export function SkeletonTable({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div className="animate-pulse">
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
        <div className="flex gap-6">
          {Array.from({ length: columns }).map((_, i) => (
            <div key={i} className="h-4 bg-gray-300 rounded flex-1"></div>
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="px-6 py-4 border-b border-gray-200">
          <div className="flex gap-6">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <div key={colIndex} className="h-4 bg-gray-200 rounded flex-1"></div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
