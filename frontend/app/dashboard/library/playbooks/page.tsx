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
import { PlaybookList } from "@/components/playbooks/PlaybookList";

export const metadata = {
  title: "Playbooks — Trade Sensei",
};

export default function PlaybooksPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Playbooks"
        subtitle="Define and manage your trading strategies and setup types"
      />
      <PlaybookList />
    </div>
  );
}
