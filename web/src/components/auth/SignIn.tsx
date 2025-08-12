import Link from "next/link";

export function SignIn(props: { redirect: string | undefined }) {
  return <Link href={props.redirect ?? "/"}>SignIn</Link>;
}

// <SignIn forceRedirectUrl={redirect} signUpForceRedirectUrl={redirect} />
