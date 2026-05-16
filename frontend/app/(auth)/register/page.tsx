/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import Image from "next/image";
import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Create Account — Trade Sensei",
};

export default function RegisterPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        {/* Logo / title */}
        <div className="flex flex-col items-center mb-8">
          <Image
            src="/logo.svg"
            alt="Trade Sensei logo"
            width={512}
            height={512}
            priority
            className="rounded-xl mb-4"
            style={{ width: "auto", maxWidth: "100%", height: "auto", maxHeight: "10rem" }}
          />
          <h1 className="text-2xl font-bold text-foreground mb-1 tracking-tight">Trade Sensei</h1>
          <p className="text-muted-foreground text-sm">
            Create your account
          </p>
        </div>

        {/* Form card */}
        <div className="bg-card rounded-2xl border border-border p-8 shadow-sm">
          <RegisterForm />

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
