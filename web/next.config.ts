import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/lyc-racing-data",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
