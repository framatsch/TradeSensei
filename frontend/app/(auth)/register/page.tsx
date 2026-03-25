import Image from "next/image";
import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Create Account — Trade Journal",
};

export default function RegisterPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="w-full max-w-md">
        {/* Logo / title */}
        <div className="flex flex-col items-center mb-8">
          <Image
            src="/logo.svg"
            alt="Trade Journal logo"
            width={512}
            height={512}
            priority
            className="rounded-xl mb-3"
            style={{ width: "auto", maxWidth: "100%", height: "auto", maxHeight: "10rem" }}
          />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Trade Journal</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            Create your account
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8">
          <RegisterForm />

          <p className="text-center text-sm text-slate-600 dark:text-slate-400 mt-6">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
