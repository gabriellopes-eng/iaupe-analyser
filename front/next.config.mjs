/** @type {import('next').NextConfig} */
const nextConfig = {
  // ESLint nao e obrigatorio para o prototipo; nao bloqueia o build.
  eslint: { ignoreDuringBuilds: true },
  // O driver do MongoDB e uma dependencia nativa; mantemos fora do bundle do servidor.
  experimental: {
    serverComponentsExternalPackages: ["mongodb"],
  },
};

export default nextConfig;
