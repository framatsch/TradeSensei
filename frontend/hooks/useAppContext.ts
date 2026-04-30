import { useAppContextStore } from '@/stores/appContextStore';

export const useAppContext = () => {
  const activeContext = useAppContextStore((state) => state.activeContext);
  const setActiveContext = useAppContextStore((state) => state.setActiveContext);

  return { activeContext, setActiveContext };
};
