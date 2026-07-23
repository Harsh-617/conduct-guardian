import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config, { dev }) => {
    // Disable the persistent filesystem cache in dev: on this machine,
    // Windows Defender's real-time scan races webpack's cache-file
    // renames (ENOENT/EPERM), which corrupts the cache and produces
    // intermittent 500s ("Unexpected end of JSON input") on unrelated
    // routes. In-memory compilation is slightly slower to rebuild but
    // avoids the race entirely.
    if (dev) {
      config.cache = false;
    }
    return config;
  },
};

export default nextConfig;
