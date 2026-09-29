import { createBrowserRouter } from "react-router-dom";
import { Home } from "../pages/Home";
import { Setup } from "../pages/Setup";
import { Interview } from "../pages/Interview";
import { Result } from "../pages/Result";

export const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/setup", element: <Setup /> },
  { path: "/interview/:id", element: <Interview /> },
  { path: "/result/:id", element: <Result /> },
]);
