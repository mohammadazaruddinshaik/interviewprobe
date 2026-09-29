import { useParams } from "react-router-dom";

export function Result() {
  const { id } = useParams<{ id: string }>();
  return <div className="p-4">Result {id}</div>;
}
