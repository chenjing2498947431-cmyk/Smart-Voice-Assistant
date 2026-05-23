/**
 * Copyright 2025 Beijing Volcano Engine Technology Co., Ltd. All Rights Reserved.
 * SPDX-license-identifier: BSD-3-Clause
 */

import { configureStore } from '@reduxjs/toolkit';
import roomSlice, { RoomState } from './slices/room';
import deviceSlice, { DeviceState } from './slices/device';
import historySlice, { HistoryState } from './slices/history';

export interface RootState {
  room: RoomState;
  device: DeviceState;
  history: HistoryState;
}

const store = configureStore({
  reducer: {
    room: roomSlice,
    device: deviceSlice,
    history: historySlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
