import Link from "next/link";

import "./globals.css";

export const metadata = {
  title: "Recall Map",
  description: "Active-recall gym: paste what you learn, review what fades.",
};

/** App Shell: one shared header with navigation wraps every page. */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="shell-header">
          <nav className="shell-nav">
            <Link href="/" className="shell-brand">
              Recall Map
            </Link>
            <Link href="/">Home</Link>
            <Link href="/topics">Topics</Link>
          </nav>
        </header>
        <main className="shell-main">{children}</main>
      </body>
    </html>
  );
}
