"use client";

import Link from "next/link";

export function SignUp(props: { redirect: string | undefined }) {
  // For now, just redirect to home when clicking sign up
  return <Link href={props.redirect ?? "/"}>SignUp</Link>;
}
