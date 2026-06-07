import { Button } from "@/components/ui/button";

// Word / PDF download pair. `path` is the docx endpoint; PDF appends ?format=pdf.
export function DownloadDocButtons({ path }: { path: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Button asChild size="sm" variant="outline">
        <a href={path}>Word</a>
      </Button>
      <Button asChild size="sm" variant="outline">
        <a href={`${path}?format=pdf`}>PDF</a>
      </Button>
    </span>
  );
}
