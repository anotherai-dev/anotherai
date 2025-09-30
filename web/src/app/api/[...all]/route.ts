import { NextRequest, NextResponse } from "next/server";
import { getToken } from "@/auth/server";

const API_URL = process.env.NEXT_PUBLIC_ANOTHERAI_API_URL ?? process.env.ANOTHERAI_API_URL ?? "http://localhost:8000";

const proxyHandler = async (req: NextRequest) => {
  const incomingUrl = new URL(req.url, `http://${req.headers.get("host")}`);
  const prefixToRemove = "/api";
  const pathWithoutPrefix = incomingUrl.pathname.replace(prefixToRemove, "");

  const targetUrl = `${pathWithoutPrefix}${incomingUrl.search}`;

  try {
    const options: RequestInit = {
      method: req.method,
      body: null as string | null,
    };

    if (req.method === "POST" || req.method === "PUT" || req.method === "PATCH" || req.method === "DELETE") {
      const bodyData = await req.text();
      if (bodyData) {
        options.body = bodyData;
      }
    }
    // Forward important headers
    const headers: Record<string, string> = {};

    // Forward Content-Type
    const contentType = req.headers.get("Content-Type");
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const token = await getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    options.headers = headers;

    const apiResponse = await fetch(`${API_URL}${targetUrl}`, options);
    const data = apiResponse.status === 204 ? null : await apiResponse.text();

    return new NextResponse(data, { status: apiResponse.status });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } catch (error: any) {
    console.error("Error forwarding request", error);
    return new NextResponse(`An error occurred while forwarding the request: ${error?.message}`, {
      status: error?.status || 500,
    });
  }
};

export const GET = proxyHandler;
export const POST = proxyHandler;
export const PUT = proxyHandler;
export const PATCH = proxyHandler;
export const DELETE = proxyHandler;
