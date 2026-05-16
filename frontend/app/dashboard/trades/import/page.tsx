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

/**
 * Import page — broker file upload form.
 */

import { PageHeader } from "@/components/ui/PageHeader";
import { ImportForm } from "@/components/imports/ImportForm";

export const metadata = {
  title: "Import — Trade Sensei",
};

export default function ImportPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="Import Trades"
        subtitle="Upload a broker activity file to import your trades"
      />
      <ImportForm />
    </div>
  );
}
