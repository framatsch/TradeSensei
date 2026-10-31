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

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnnotationEditor } from '@/components/checkin/AnnotationEditor';
import type { AnnotationDefinitionResponse, CheckinAnnotationResponse } from '@/lib/api/types.gen';
import { 
  useAssignCheckinAnnotation, 
  useUpdateCheckinAnnotation, 
  useRemoveCheckinAnnotation 
} from '@/hooks/useCheckinMetadata';

jest.mock('@/hooks/useCheckinMetadata', () => ({
  useAssignCheckinAnnotation: jest.fn(),
  useUpdateCheckinAnnotation: jest.fn(),
  useRemoveCheckinAnnotation: jest.fn(),
}));

const mockDefinitions: AnnotationDefinitionResponse[] = [
  { 
    id: 'def-1', 
    name: 'Mood', 
    type: 'string_enum', 
    scope: 'checkins', 
    scale_labels: { options: ['Happy', 'Sad'] },
    is_archived: false,
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    description: null,
    icon_identifier: null
  },
  {
    id: 'def-2',
    name: 'Done',
    type: 'bool',
    scope: 'checkins',
    is_archived: false,
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    description: null,
    icon_identifier: null,
    scale_labels: null
  }
];

describe('AnnotationEditor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAssignCheckinAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useUpdateCheckinAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useRemoveCheckinAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
  });

  it('calls onBufferChange when checkinId is null', () => {
    const onBufferChange = jest.fn();
    render(
      <AnnotationEditor 
        checkinId={null} 
        definitions={mockDefinitions} 
        assigned={[]} 
        onBufferChange={onBufferChange} 
      />
    );
    
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Happy' } });
    expect(onBufferChange).toHaveBeenCalledWith('def-1', 'Happy');
  });

  it('calls assign mutation for new assignment when checkinId is provided', async () => {
    const mutateAsync = jest.fn();
    (useAssignCheckinAnnotation as jest.Mock).mockReturnValue({ mutateAsync });
    
    render(
      <AnnotationEditor 
        checkinId="checkin-123" 
        definitions={[mockDefinitions[0]]} 
        assigned={[]} 
      />
    );
    
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Happy' } });
    expect(mutateAsync).toHaveBeenCalledWith({ 
      checkinId: 'checkin-123', 
      annotationDefinitionId: 'def-1', 
      value: 'Happy' 
    });
  });

  it('calls update mutation for existing assignment', async () => {
    const mutateAsync = jest.fn();
    (useUpdateCheckinAnnotation as jest.Mock).mockReturnValue({ mutateAsync });
    
    const assigned: CheckinAnnotationResponse[] = [{
      annotation_definition_id: 'def-1',
      name: 'Mood',
      type: 'string_enum',
      scope: 'checkins',
      value: 'Sad',
      icon_identifier: null
    }];

    render(
      <AnnotationEditor 
        checkinId="checkin-123" 
        definitions={[mockDefinitions[0]]} 
        assigned={assigned} 
      />
    );
    
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Happy' } });
    expect(mutateAsync).toHaveBeenCalledWith({ 
      checkinId: 'checkin-123', 
      annotationDefinitionId: 'def-1', 
      value: 'Happy' 
    });
  });

  it('renders bool toggle and calls onBufferChange', () => {
    const onBufferChange = jest.fn();
    render(
      <AnnotationEditor 
        checkinId={null} 
        definitions={[mockDefinitions[1]]} 
        assigned={[]} 
        onBufferChange={onBufferChange} 
      />
    );
    
    const toggle = screen.getByLabelText('Toggle Done');
    fireEvent.click(toggle);
    expect(onBufferChange).toHaveBeenCalledWith('def-2', true);
  });
});
