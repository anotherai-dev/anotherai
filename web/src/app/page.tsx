import { redirect } from "next/navigation";
import HomePage from "@/app/home/page";
import { SignedIn, SignedOut } from "@/auth/components";

export default function Home() {
  return (
    <>
      <SignedIn>
        <RedirectToCompletions />
      </SignedIn>
      <SignedOut>
        <HomePage />
      </SignedOut>
    </>
  );
}

function RedirectToCompletions() {
  redirect("/completions");
  return null; // This will never be reached due to redirect, but satisfies TypeScript
}
