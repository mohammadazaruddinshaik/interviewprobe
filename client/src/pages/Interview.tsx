import { useParams } from "react-router-dom";

export function Interview() {
  const { id } = useParams<{ id: string }>();
  return <div className="p-4">Interview {id}</div>;
}
