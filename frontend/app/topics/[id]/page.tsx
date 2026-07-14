import Link from "next/link";

/** Topic Page placeholder: mastery overview and Concept Map arrive in later slices. */
export default async function TopicPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>Topic</h1>
      <p>Topic id: {id}</p>
      <p>This Topic Page will show mastery and the Concept Map in later slices.</p>
      <Link href="/topics">Back to topics</Link>
    </main>
  );
}
