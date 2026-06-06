# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys

file_path = "/home/scheffold/work/TradeSensei/frontend/components/library/TaxonomyManager.tsx"
with open(file_path, "r") as f:
    content = f.read()

new_row1 = """
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  aria-label="Tag name"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-muted-foreground/50 disabled:opacity-50"
                  placeholder="e.g. FOMO, High Conviction"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button 
                      type="button"
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    >
                      <span className="truncate pr-2">
                        {scope === "both" ? "Trades & Check-ins" : scope === "trades" ? "Trades" : scope === "checkins" ? "Check-ins" : "Playbook"}
                      </span>
                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content className="w-56 rounded-lg bg-card border border-border shadow-lg p-2 z-50">
                      <DropdownMenu.CheckboxItem
                        checked={scope === "trades" || scope === "both"}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setScope(scope === "checkins" ? "both" : "trades");
                          } else {
                            setScope(scope === "both" ? "checkins" : "trades");
                          }
                        }}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Trades</span>
                      </DropdownMenu.CheckboxItem>

                      <DropdownMenu.CheckboxItem
                        checked={scope === "checkins" || scope === "both"}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setScope(scope === "trades" ? "both" : "checkins");
                          } else {
                            setScope(scope === "both" ? "trades" : "checkins");
                          }
                        }}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Check-ins</span>
                      </DropdownMenu.CheckboxItem>

                      <DropdownMenu.Separator className="h-px bg-border my-1" />

                      <DropdownMenu.CheckboxItem
                        checked={scope === "playbook"}
                        onCheckedChange={(checked) => {
                          if (checked) setScope("playbook");
                          else setScope("trades"); // default fallback
                        }}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Playbook</span>
                      </DropdownMenu.CheckboxItem>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Icon
                </label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button 
                      type="button"
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <DynamicIcon name={iconIdentifier || "tag"} className="w-4 h-4 text-muted-foreground shrink-0" />
                        <span className="truncate">{iconIdentifier || "Select icon..."}</span>
                      </div>
                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content className="w-64 rounded-lg bg-card border border-border shadow-lg p-2 z-50 max-h-60 overflow-y-auto">
                      <div className="grid grid-cols-4 gap-2">
                        {["tag", "trending-up", "trending-down", "alert-circle", "check-circle", "book-open", "zap", "target", "shield", "bar-chart-2", "activity", "clock", "calendar", "star", "bookmark", "flag", "heart", "award", "thumbs-up", "thumbs-down"].map((iconName) => (
                          <DropdownMenu.Item
                            key={iconName}
                            onSelect={() => setIconIdentifier(iconName)}
                            className="flex items-center justify-center p-2 hover:bg-secondary rounded cursor-pointer outline-none transition-colors"
                            title={iconName}
                          >
                            <DynamicIcon name={iconName} className="w-5 h-5 text-foreground" />
                          </DropdownMenu.Item>
                        ))}
                      </div>
                      <div className="mt-2 pt-2 border-t border-border">
                        <input
                          type="text"
                          value={iconIdentifier}
                          onChange={(e) => setIconIdentifier(e.target.value)}
                          className="w-full px-2 py-1 bg-secondary border border-border rounded-md text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground/50"
                          placeholder="Or type lucide name..."
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            </div>

            {/* ROW 2: Description */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={createMutation.isPending || updateMutation.isPending}
                aria-label="Tag description"
                className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-muted-foreground/50 disabled:opacity-50"
                placeholder="Optional description..."
              />
            </div>
"""

form_start = content.find("<form onSubmit={handleSubmit} className=\"space-y-4\">")
form_end = content.find("<div className=\"flex justify-end gap-3 pt-2\">")

if form_start != -1 and form_end != -1:
    new_content = content[:form_start + len("<form onSubmit={handleSubmit} className=\"space-y-4\">")] + new_row1 + "\n\n" + """            {/* ROW 3: Color */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Color
              </label>
              <div className="flex flex-wrap gap-2 pt-1">
                {THEME_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={"color " + c}
                    aria-pressed={colorHex === c}
                    onClick={() => setColorHex(c)}
                    className={"w-6 h-6 rounded-full transition-all " + (
                      colorHex === c
                        ? "ring-2 ring-offset-2 ring-offset-background ring-primary scale-110"
                        : "hover:scale-110 opacity-80"
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>\n\n            """ + content[form_end:]

    # Fix imports
    if "ChevronDown" not in new_content:
        new_content = new_content.replace(
            'import { Plus, Edit2, Trash2, Archive, Loader2, AlertCircle } from "lucide-react";',
            'import { Plus, Edit2, Trash2, Archive, Loader2, AlertCircle, ChevronDown, Check } from "lucide-react";\nimport * as DropdownMenu from "@radix-ui/react-dropdown-menu";'
        )

    with open(file_path, "w") as f:
        f.write(new_content)
    print("Success")
else:
    print("Form not found")
