export const state = {
  token: null,
  user: null,
  status: null,
  houses: new Map(),
  selectedHouse: null,
  editingDevice: null,
  config: null,
  pricesDate: null,
  pricesCount: 0,
  trades: [],             // tranzacții P2P recente, cea mai nouă prima
};
