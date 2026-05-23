/**
 * 历史会话侧栏。
 * - 顶部 "新建会话" 按钮: 清 currentSid + msgHistory
 * - 列表: 每项点击 = 切换 currentSid + 拉历史消息回填 msgHistory
 * - 每项有删除按钮
 *
 * 注意: 当用户处于通话中 (isAIGCEnable=true), 切换会话会丢失正在进行的对话上下文,
 * 所以这种情况下点击按钮会被拦截并提示。
 */

import { useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Button, Message, Popconfirm } from '@arco-design/web-react';
import { RootState } from '@/store';
import {
  setConversations,
  setCurrentSid,
  setLoading,
  removeConversation,
} from '@/store/slices/history';
import { setMsgHistory, clearHistoryMsg, Msg } from '@/store/slices/room';
import * as llmApi from '@/lib/llmServerApi';
import styles from './index.module.less';

function HistorySidebar() {
  const dispatch = useDispatch();
  const { conversations, currentSid, loading } = useSelector((s: RootState) => s.history);
  const { isAIGCEnable } = useSelector((s: RootState) => s.room);

  const refresh = useCallback(async () => {
    dispatch(setLoading(true));
    try {
      const list = await llmApi.listConversations();
      dispatch(setConversations(list));
    } catch (e) {
      console.warn('[history] 拉列表失败', e);
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const guardInCall = (): boolean => {
    if (isAIGCEnable) {
      Message.warning('通话进行中, 请先挂断再切换会话');
      return true;
    }
    return false;
  };

  const handleNew = () => {
    if (guardInCall()) return;
    dispatch(setCurrentSid(''));
    dispatch(clearHistoryMsg());
  };

  const handlePick = async (sid: string) => {
    if (guardInCall()) return;
    if (sid === currentSid) return;
    try {
      const detail = await llmApi.getConversation(sid);
      // DB role -> Msg.user 字段: 用 'user'/'assistant' 作为标签,
      // Conversation.tsx 已经认这两个值
      const replay: Msg[] = detail.messages.map((m) => ({
        value: m.content,
        time: new Date(m.created_at * 1000).toString(),
        user: m.role,
        definite: true,
        paragraph: true,
      }));
      dispatch(setCurrentSid(sid));
      dispatch(setMsgHistory(replay));
    } catch (e) {
      Message.error(`加载会话失败: ${(e as Error).message}`);
    }
  };

  const handleDelete = async (sid: string) => {
    try {
      await llmApi.deleteConversation(sid);
      dispatch(removeConversation(sid));
      if (sid === currentSid) {
        dispatch(clearHistoryMsg());
      }
    } catch (e) {
      Message.error(`删除失败: ${(e as Error).message}`);
    }
  };

  return (
    <div className={styles.sidebar}>
      <div className={styles.header}>
        <span className={styles.title}>历史会话</span>
        <Button size="mini" type="primary" onClick={handleNew}>
          + 新建
        </Button>
      </div>
      <div className={styles.list}>
        {loading && conversations.length === 0 ? (
          <div className={styles.empty}>加载中...</div>
        ) : conversations.length === 0 ? (
          <div className={styles.empty}>暂无会话</div>
        ) : (
          conversations.map((c) => {
            const active = c.sid === currentSid;
            return (
              <div
                key={c.sid}
                className={`${styles.item} ${active ? styles.itemActive : ''}`}
                onClick={() => handlePick(c.sid)}
              >
                <div className={styles.itemMain}>
                  <div className={styles.itemTitle}>{c.title || '新会话'}</div>
                  {c.last_message ? (
                    <div className={styles.itemPreview}>{c.last_message}</div>
                  ) : null}
                  <div className={styles.itemTime}>
                    {new Date(c.updated_at * 1000).toLocaleString()}
                  </div>
                </div>
                <Popconfirm
                  title="确认删除该会话?"
                  onOk={(e) => {
                    e?.stopPropagation();
                    handleDelete(c.sid);
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                >
                  <Button
                    size="mini"
                    type="text"
                    status="danger"
                    onClick={(e) => e.stopPropagation()}
                  >
                    删
                  </Button>
                </Popconfirm>
              </div>
            );
          })
        )}
      </div>
      <div className={styles.footer}>
        <Button size="mini" long onClick={refresh} loading={loading}>
          刷新列表
        </Button>
      </div>
    </div>
  );
}

export default HistorySidebar;
