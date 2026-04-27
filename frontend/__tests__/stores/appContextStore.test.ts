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
