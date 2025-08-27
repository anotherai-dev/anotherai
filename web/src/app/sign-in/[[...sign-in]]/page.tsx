import Image from "next/image";
import { SignIn } from "@/auth/components";
import { useParsedSearchParams } from "@/lib/queryString";

export default function Page() {
  const { redirect } = useParsedSearchParams("redirect");

  return (
    <div className="flex flex-col w-full h-screen bg-gray-50 justify-center items-center px-4">
      <div className="bg-white rounded-[2px] border border-gray-200 p-6 max-w-md w-full text-center shadow-sm">
        {/* Logo and Title */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={40} height={40} className="w-10 h-10" />
          <h1 className="text-2xl font-semibold text-gray-900">AnotherAI</h1>
        </div>

        <div className="mb-6">
          <p className="text-sm text-gray-600">Welcome back! Please sign in to your account</p>
        </div>

        <SignIn redirect={redirect} />
      </div>
    </div>
  );
}
