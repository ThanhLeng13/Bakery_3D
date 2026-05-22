export default function SkeletonCard() {
  return (
    <div
      className="rounded-2xl bg-white shadow-sm overflow-hidden"
      aria-hidden="true"
      aria-busy="true"
    >
      {/* Image placeholder – same aspect-ratio as real card (prevents CLS) */}
      <div className="aspect-square skeleton" />

      {/* Content placeholder */}
      <div className="p-3 sm:p-4 space-y-2">
        {/* Name */}
        <div className="skeleton h-4 sm:h-5 rounded w-3/4" />
        {/* Description – hidden on mobile same as real card */}
        <div className="hidden sm:block space-y-1.5">
          <div className="skeleton h-3.5 rounded w-full" />
          <div className="skeleton h-3.5 rounded w-2/3" />
        </div>
        {/* Price */}
        <div className="skeleton h-4 sm:h-5 rounded w-1/3" />
        {/* Rating */}
        <div className="skeleton h-3.5 rounded w-1/2" />
      </div>
    </div>
  );
}
