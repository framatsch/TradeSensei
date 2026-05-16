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

"""Pydantic schemas for playbook taxonomy assignments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaybookTaxonomyCreate(BaseModel):
    """Payload for assigning a taxonomy to a playbook."""

    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy definition UUID to assign.")


class PlaybookTaxonomyResponse(BaseModel):
    """Response schema for a playbook taxonomy assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Assignment identifier.")
    playbook_id: uuid.UUID = Field(..., description="Playbook identifier.")
    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy identifier.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
