/**
 * 历史对话 store: 列表 + 当前选中的 sid。
 * currentSid 决定下次 StartVoiceChat 用哪个上下文; 为空时 Server_py 会新建。
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { ConversationSummary } from '@/lib/llmServerApi';

export interface HistoryState {
  conversations: ConversationSummary[];
  currentSid: string;
  loading: boolean;
}

const initialState: HistoryState = {
  conversations: [],
  currentSid: '',
  loading: false,
};

const slice = createSlice({
  name: 'history',
  initialState,
  reducers: {
    setConversations: (state, { payload }: PayloadAction<ConversationSummary[]>) => {
      state.conversations = payload;
    },
    setCurrentSid: (state, { payload }: PayloadAction<string>) => {
      state.currentSid = payload;
    },
    setLoading: (state, { payload }: PayloadAction<boolean>) => {
      state.loading = payload;
    },
    removeConversation: (state, { payload }: PayloadAction<string>) => {
      state.conversations = state.conversations.filter((c) => c.sid !== payload);
      if (state.currentSid === payload) {
        state.currentSid = '';
      }
    },
  },
});

export const { setConversations, setCurrentSid, setLoading, removeConversation } = slice.actions;
export default slice.reducer;
