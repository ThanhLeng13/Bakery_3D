/** @type {import('next').NextConfig} */
const nextConfig = {
  // --- Image Optimization ---
  images: {
    // Allow remote image domains (Supabase Storage + placeholder)
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
      {
        protocol: "https",
        hostname: "placehold.co",
      },
    ],
    // Responsive image sizes used by Next.js Image component
    deviceSizes: [320, 480, 640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    formats: ["image/avif", "image/webp"],
    // Minimum cache TTL 60 seconds
    minimumCacheTTL: 60,
    // Allow SVG via dangerouslyAllowSVG (disabled for security, use <img> for SVGs)
    dangerouslyAllowSVG: false,
  },

  // --- Experimental optimizations ---
  experimental: {
    // Optimize CSS delivery (removes render-blocking CSS)
    optimizeCss: false, // keep false to avoid critters dependency issues
    // Partial Pre-rendering (Next.js 14 feature flag)
    // ppr: true, // uncomment when stable
  },

  // --- Compression ---
  compress: true,

  // --- Bundle Analysis (set ANALYZE=true to run) ---
  // Bundle analyzer disabled by default; enable with: ANALYZE=true npm run build

  // --- Headers for performance and security ---
  async headers() {
    const isDev = process.env.NODE_ENV === "development";

    // Base connect-src always includes self + Supabase
    // NEXT_PUBLIC_API_URL: added when set so that production deployments where
    // the API backend lives on a different origin (e.g. https://api.bo-no.com)
    // are not blocked by CSP. Has no effect when unset or same-origin.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const connectSrc = [
      "'self'",
      "https://*.supabase.co",
      "wss://*.supabase.co",
      // External API backend (production): include only when explicitly configured
      ...(apiUrl ? [apiUrl] : []),
      // Local backend origins: only in development
      ...(isDev ? ["http://127.0.0.1:8000", "http://localhost:8000"] : []),
    ].join(" ");

    return [
      {
        source: "/(.*)",
        headers: [
          // Prevents MIME-type sniffing
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Prevents clickjacking — DENY to match vercel.json
          { key: "X-Frame-Options", value: "DENY" },
          // XSS protection (legacy but harmless)
          { key: "X-XSS-Protection", value: "1; mode=block" },
          // Referrer policy
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Content Security Policy
          // - 'unsafe-inline' in script-src: required because Next.js SSR hydration
          //   injects inline <script> tags for __NEXT_DATA__ and chunk preloading.
          //   Removing it breaks client-side hydration entirely.
          // - 'unsafe-eval' in script-src: added ONLY in development because Next.js
          //   Fast Refresh and HMR rely on eval(). Without it, the console is flooded
          //   with CSP errors and hot reloading breaks. Excluded in production.
          // - 'unsafe-inline' in style-src: required because Next.js injects inline
          //   <style> tags for CSS-in-JS and styled-jsx during SSR.
          // - WebGL shader compilation (gl.shaderSource, gl.compileShader) uses GPU
          //   APIs and is NOT affected by CSP script-src; no 'unsafe-eval' needed.
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: blob: https://*.supabase.co https://placehold.co",
              `connect-src ${connectSrc}`,
              "worker-src 'self' blob:",
              "frame-ancestors 'self'",
            ].join("; "),
          },
        ],
      },
      {
        // Cache static assets aggressively
        source: "/static/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },

  // --- Redirects ---
  async redirects() {
    return [
      // Redirect /admin to /admin/products (default admin page)
      {
        source: "/admin",
        destination: "/admin/products",
        permanent: false,
      },
      // Redirect /baker to /baker/orders (default baker page)
      {
        source: "/baker",
        destination: "/baker/orders",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
