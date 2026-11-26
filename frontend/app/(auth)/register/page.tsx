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

import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Create Account — Trade Sensei",
};

export default function RegisterPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center p-4">
      <section className="solid-card w-full space-y-4 p-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo size={72} className="rounded-2xl" />
          <h1 className="text-2xl font-semibold text-foreground">Create your account</h1>
        </div>

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
      </section>
    </main>
  );
}
