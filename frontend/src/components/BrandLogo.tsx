import Image from "next/image";

export default function BrandLogo({ className = "", priority = false }: { className?: string; priority?: boolean }) {
  return (
    <Image
      src="/brand/bo-no-logo.png"
      alt="Bơ Nơ Bakery"
      width={6380}
      height={2455}
      sizes="(max-width: 640px) 120px, 152px"
      priority={priority}
      className={`h-auto w-[120px] sm:w-[152px] ${className}`}
    />
  );
}
