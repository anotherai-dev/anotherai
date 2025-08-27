"use server";

import { NextFetchEvent, NextRequest, NextResponse } from "next/server";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function middleware(request: NextRequest, event: NextFetchEvent) {
  return NextResponse.next();
}

export async function getToken() {
  return null;
}
