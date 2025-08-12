"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { Modal } from "../Modal";
import { ApiKeysModalContent } from "./ApiKeysModalContent";

export function ApiKeysModal() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const showModal = searchParams.get("showManageKeysModal") === "true";
  const isOpen = showModal;

  const closeModal = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    params.delete("showManageKeysModal");
    const newUrl = `${window.location.pathname}${
      params.toString() ? `?${params.toString()}` : ""
    }`;
    router.replace(newUrl, { scroll: false });
  }, [searchParams, router]);

  if (!showModal) {
    return null;
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <ApiKeysModalContent onClose={closeModal} />
    </Modal>
  );
}
