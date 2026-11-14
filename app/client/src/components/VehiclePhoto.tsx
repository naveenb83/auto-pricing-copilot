import { AspectRatio } from '@databricks/appkit-ui/react';
import { Car } from 'lucide-react';
import { useState } from 'react';

/** Openly licensed Wikimedia Commons photo served from the UC volume via the files plugin (read-only). */
export function VehiclePhoto({ file, alt, credit, className }: { file: string; alt: string; credit?: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const src = `/api/files/files/raw?path=${encodeURIComponent(file)}`;
  return (
    <figure className={className}>
      <AspectRatio ratio={16 / 10} className="overflow-hidden rounded-md bg-muted">
        {file && !failed ? (
          <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <Car className="h-8 w-8" aria-hidden />
          </div>
        )}
      </AspectRatio>
      {credit && <figcaption className="mt-1 text-[11px] leading-tight text-muted-foreground">{credit}</figcaption>}
    </figure>
  );
}
