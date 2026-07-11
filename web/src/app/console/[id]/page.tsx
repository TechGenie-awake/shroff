import { HealthCard } from "@/components/health-card";

export default async function HealthCardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <HealthCard id={id.toUpperCase()} />;
}
