import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only enable standalone output when building with Docker
  ...(process.env.DOCKER_BUILD ? { output: "standalone" } : {}),
};

export default nextConfig;
