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

import { PageHeader } from "@/components/ui/PageHeader";
import { TaxonomyManager } from "@/components/library/TaxonomyManager";

export const metadata = {
  title: "Tags — Trade Sensei",
};

export default function TagsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Tags"
        subtitle="Manage reusable metadata taxonomies for trades and check-ins"
      />
      <TaxonomyManager />
    </div>
  );
}
