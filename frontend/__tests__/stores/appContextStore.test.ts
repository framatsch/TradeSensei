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

import { useAppContextStore } from '../../stores/appContextStore';

describe('appContextStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useAppContextStore.setState({ activeContext: 'portfolio', hydrated: false });
  });

  it('hydrates from localStorage if valid context', () => {
    localStorage.setItem('active_app_context', 'library');
    useAppContextStore.getState().hydrate();
    
    expect(useAppContextStore.getState().activeContext).toBe('library');
    expect(useAppContextStore.getState().hydrated).toBe(true);
  });

  it('defaults to portfolio if invalid context in localStorage', () => {
    localStorage.setItem('active_app_context', 'invalid_context');
    useAppContextStore.getState().hydrate();
    
    expect(useAppContextStore.getState().activeContext).toBe('portfolio');
    expect(useAppContextStore.getState().hydrated).toBe(true);
  });

  it('defaults to portfolio if localStorage is empty', () => {
    useAppContextStore.getState().hydrate();
    
    expect(useAppContextStore.getState().activeContext).toBe('portfolio');
    expect(useAppContextStore.getState().hydrated).toBe(true);
  });

  it('setActiveContext updates state and persists to localStorage', () => {
    useAppContextStore.getState().setActiveContext('checkin');
    
    expect(useAppContextStore.getState().activeContext).toBe('checkin');
    expect(localStorage.getItem('active_app_context')).toBe('checkin');
  });
});
