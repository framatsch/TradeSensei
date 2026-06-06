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
import { AnnotationFilterRows, AnnotationFilterRow } from '@/components/ui/AnnotationFilterRows';
import { AnnotationDefinitionResponse } from '@/lib/api/types.gen';

const mockDefinitions: AnnotationDefinitionResponse[] = [
  { 
    id: 'def-1', 
    name: 'Mood', 
    type: 'string_enum', 
    scope: 'both', 
    scale_labels: { options: ['Happy', 'Sad'] }, 
    is_archived: false, 
    created_at: '2024-01-01', 
    updated_at: '2024-01-01',
    description: null,
    icon_identifier: null
  },
  { 
    id: 'def-2', 
    name: 'Score', 
    type: 'int', 
    scope: 'both', 
    scale_labels: { min: 0, max: 100 }, 
    is_archived: false, 
    created_at: '2024-01-01', 
    updated_at: '2024-01-01',
    description: null,
    icon_identifier: null
  },
];

describe('AnnotationFilterRows', () => {
  it('renders nothing when no definitions are provided', () => {
    const { container } = render(<AnnotationFilterRows rows={[]} definitions={[]} onChange={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders existing rows and allows adding a new row', () => {
    const onChange = jest.fn();
    const rows: AnnotationFilterRow[] = [{ annotation_definition_id: 'def-1', operator: 'eq', value: 'Happy', logic: 'and' }];
    render(
      <AnnotationFilterRows 
        rows={rows} 
        definitions={mockDefinitions} 
        onChange={onChange} 
      />
    );

    expect(screen.getByDisplayValue('Mood')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Happy')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Add'));
    expect(onChange).toHaveBeenCalledWith([
      ...rows,
      { annotation_definition_id: 'def-1', operator: 'eq', value: 'Happy', logic: 'and', _key: expect.any(String) }
    ]);
  });

  it('changes operators based on definition type', () => {
    const onChange = jest.fn();
    const { rerender } = render(
      <AnnotationFilterRows 
        rows={[{ annotation_definition_id: 'def-1', operator: 'eq', value: 'Happy', logic: 'and' }]} 
        definitions={mockDefinitions} 
        onChange={onChange} 
      />
    );
    
    // def-1 is string_enum, options should include "is" and "is not"
    expect(screen.getByText('is')).toBeInTheDocument();
    expect(screen.getByText('is not')).toBeInTheDocument();

    rerender(
      <AnnotationFilterRows 
        rows={[{ annotation_definition_id: 'def-2', operator: 'eq', value: 50, logic: 'and' }]} 
        definitions={mockDefinitions} 
        onChange={onChange} 
      />
    );
    // def-2 is int, operators should include "=" and ">"
    expect(screen.getByText('=')).toBeInTheDocument();
    expect(screen.getByText('>')).toBeInTheDocument();
  });

  it('toggles logic between AND and OR', () => {
    const onChange = jest.fn();
    const rows: AnnotationFilterRow[] = [
      { annotation_definition_id: 'def-1', operator: 'eq', value: 'Happy', logic: 'and', _key: 'key-1' },
      { annotation_definition_id: 'def-2', operator: 'eq', value: 50, logic: 'and', _key: 'key-2' }
    ];
    render(
      <AnnotationFilterRows 
        rows={rows} 
        definitions={mockDefinitions} 
        onChange={onChange} 
      />
    );

    const andPill = screen.getByTitle('Click to toggle AND / OR');
    expect(andPill).toHaveTextContent('AND');
    
    fireEvent.click(andPill);
    expect(onChange).toHaveBeenCalledWith([
      rows[0],
      { ...rows[1], logic: 'or' }
    ]);
  });

  it('removes a row when X is clicked', () => {
    const onChange = jest.fn();
    const rows: AnnotationFilterRow[] = [{ annotation_definition_id: 'def-1', operator: 'eq', value: 'Happy', logic: 'and' }];
    render(
      <AnnotationFilterRows 
        rows={rows} 
        definitions={mockDefinitions} 
        onChange={onChange} 
      />
    );

    fireEvent.click(screen.getByLabelText('Remove filter'));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
