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
    return [
      {
        source: "/(.*)",
        headers: [
          // Prevents MIME-type sniffing
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Prevents clickjacking
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          // XSS protection (legacy but harmless)
          { key: "X-XSS-Protection", value: "1; mode=block" },
          // Referrer policy
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // CSP: allow eval for Three.js WebGL shader compilation
          // Three.js REQUIRES 'unsafe-eval' to compile GLSL shaders at runtime
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: blob: https://*.supabase.co https://placehold.co",
              "connect-src 'self' https://*.supabase.co wss://*.supabase.co http://127.0.0.1:8000 http://localhost:8000",
              "worker-src 'self' blob:",
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
