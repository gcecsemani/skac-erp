/** Whether Finalize Invoice should open the OS print dialog. Off by default. */

const KEY = "skac_open_print_dialog";

export function getOpenPrintDialog(): boolean {
  return localStorage.getItem(KEY) === "1";
}

export function setOpenPrintDialog(on: boolean) {
  localStorage.setItem(KEY, on ? "1" : "0");
}
