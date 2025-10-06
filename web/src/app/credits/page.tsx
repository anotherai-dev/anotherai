import { redirect } from "next/navigation";

export default function CreditsRedirect() {
  return redirect("/completions?credits=true");
}
