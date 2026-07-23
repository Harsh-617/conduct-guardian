import { Sidebar } from "@/components/sidebar";
import { PageTransition } from "@/components/page-transition";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-paper">
      <Sidebar />
      <div className="flex-1 md:ml-60">
        <main className="min-h-screen px-6 pb-10 pt-20 md:px-10 md:pt-10">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </div>
  );
}
