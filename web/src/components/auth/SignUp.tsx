import Link from "next/link";

export function SignUp(props: { redirect: string | undefined }) {
  return <Link href={props.redirect ?? "/sign-up"}>SignUp</Link>;
}

// <SignUp forceRedirectUrl={redirect} />
