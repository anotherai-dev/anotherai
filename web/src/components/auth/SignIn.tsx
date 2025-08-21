"use client";

import Link from "next/link";

export function SignIn(props: { redirect: string | undefined }) {
  // For now, just redirect to home when clicking sign in
  return <Link href={props.redirect ?? "/"}>SignIn</Link>;
}
