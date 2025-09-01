import type { AuthServer } from "../base";
import * as mod from "./server";

// Simple check for types

declare function satisfy<T>(_x: T): void;

satisfy<AuthServer>(mod); // error if not assignable
