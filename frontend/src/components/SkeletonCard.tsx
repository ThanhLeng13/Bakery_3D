export default function SkeletonCard() {
  return (
    <div
      className="animate-pulse rounded-2xl bg-white shadow-sm overflow-hidden"
      aria-hidden="true"
    >
      {/* Image placeholder */}
      <div className="aspect-square bg-gray-200" />
      {/* Content placeholder */}
      <div className="p-4 space-y-3">
        {/* Name */}
        <div className="h-5 bg-gray-200 rounded w-3/4" />
        {/* Description */}
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-2/3" />
        {/* Price */}
        <div className="h-5 bg-gray-200 rounded w-1/3" />
        {/* Rating */}
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  );
}
