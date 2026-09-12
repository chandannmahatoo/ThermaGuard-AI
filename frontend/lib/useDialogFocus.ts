import {useEffect, useRef} from 'react';
export function useDialogFocus<T extends HTMLElement>(open = true) {
  const ref = useRef<T>(null);
  useEffect(()=>{
    if (!open || !ref.current) return;
    const previous = document.activeElement as HTMLElement | null;
    const panel = ref.current;
    const focusable = () => Array.from(panel.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')).filter(el=>el.getClientRects().length>0);
    focusable()[0]?.focus();
    function trap(e:KeyboardEvent) {
      const dialogs = document.querySelectorAll('[aria-modal="true"]');
      if (e.key !== 'Tab' || dialogs[dialogs.length-1] !== panel) return;
      const items = focusable(); const first = items[0], last=items[items.length-1];
      if (!first) {e.preventDefault();return;}
      if (e.shiftKey && (document.activeElement===first || !panel.contains(document.activeElement))) {e.preventDefault();last.focus();}
      else if (!e.shiftKey && (document.activeElement===last || !panel.contains(document.activeElement))) {e.preventDefault();first.focus();}
    }
    document.addEventListener('keydown',trap);
    return ()=>{document.removeEventListener('keydown',trap);if(previous?.isConnected)previous.focus();};
  },[open]);
  return ref;
}
