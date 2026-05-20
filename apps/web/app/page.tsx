import { redirect } from "next/navigation";

export default function Home() {
  // Next.js middleware handles redirecting to /dashboard if logged in,
  // or /login if not. We just redirect to /dashboard to trigger it.
  redirect("/dashboard");
}
