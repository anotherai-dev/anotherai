import type { Components } from "../base";
import * as mod from "./components";

// Simple check for types

declare function satisfy<T>(_x: T): void;

satisfy<Components>(mod); // error if not assignable
